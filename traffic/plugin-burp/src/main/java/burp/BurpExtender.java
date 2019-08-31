package burp;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import flow.Utils;
import frame.MainPanel;

import javax.swing.*;
import java.awt.*;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;
import java.net.URL;

public class BurpExtender implements IBurpExtender, ITab, IHttpListener {
    private static final String EXTENSION_NAME = "authcheck";
    private static final String TAB_CAPTION = "AuthCheck";

    public static String UNIQUE_NAME = null;  // 全局的一个唯一用户名
    public static String UNIQUE_UID = null;     // 标识用户身份的uid


    private static URL API_URL = null;
    public static String AC_SERVER = "http://127.0.0.1";  // 越权检测服务器host

    // 全局变量
    public static boolean SCAN_FLAG = false;  // 扫描标识

    public static PrintStream STDOUT = System.out;
    public static PrintStream STDERR = System.err;

    public IBurpExtenderCallbacks callbacks = null;
    public MainPanel jPanelMain = null;

    public void registerExtenderCallbacks(IBurpExtenderCallbacks callbacks) {
        STDOUT = new PrintStream(callbacks.getStdout());
        STDERR = new PrintStream(callbacks.getStderr());
        this.callbacks = callbacks;

        this.callbacks.setExtensionName(EXTENSION_NAME);
        this.callbacks.registerHttpListener(this);

        SwingUtilities.invokeLater(() -> {
            AC_SERVER = JOptionPane.showInputDialog(null, "请输入服务器地址：", "http://127.0.0.1");
            jPanelMain = new MainPanel();
            this.callbacks.customizeUiComponent(jPanelMain);
            this.callbacks.addSuiteTab(this);
        });
    }

    public static byte[] genRedirectAC() {
        return ("HTTP/1.1 302 Moved Temporarily\n" +
                "Location: " + AC_SERVER + "/api/identify\n" +
                "Content-Length: 0\n" +
                "Cache-Control: max-age=0, no-cache, no-store\n" +
                "Pragma: no-cache\n" +
                "Connection: close\n" +
                "\n").getBytes();
    }

    public static byte[] genRedirectACSite() {
        return ("HTTP/1.1 302 Moved Temporarily\n" +
                "Location: " + AC_SERVER + "\n" +
                "Content-Length: 0\n" +
                "Cache-Control: max-age=0, no-cache, no-store\n" +
                "Pragma: no-cache\n" +
                "Connection: close\n" +
                "\n").getBytes();
    }

    public void processHttpMessage(int toolFlag, boolean messageIsRequest, IHttpRequestResponse messageInfo) {
        if (UNIQUE_NAME == null && IBurpExtenderCallbacks.TOOL_PROXY == toolFlag) {  // 使用proxy时未经过认证
            if (!messageIsRequest) {  // 响应
                identify(messageInfo);
            }
            return;
        }

        if (!SCAN_FLAG) {  // 扫描
            return;
        }

        if (toolFlag != IBurpExtenderCallbacks.TOOL_PROXY || !messageIsRequest) {
            return;
        }
        IRequestInfo requestInfo = callbacks.getHelpers().analyzeRequest(messageInfo);
        if (requestInfo == null) {
            STDERR.println("requestInfo is null...");
            return;
        }

        if(requestInfo.getUrl().toString().startsWith(AC_SERVER)){ // 不扫描本站
            return;
        }

        String ext = Utils.genExt(requestInfo.getUrl().getPath());
        if (Utils.filterFlowByExt(ext) ||
                Utils.filterFlowByHost(requestInfo.getUrl().getHost())) {  // 根据后缀和host过滤一些请求
            return;
        }

        // 越权检测
        new Thread(() -> authCheck(messageInfo, requestInfo)).start();
    }

    /**
     * 越权检测
     *
     * @param messageInfo
     * @param requestInfo
     */
    private void authCheck(IHttpRequestResponse messageInfo, IRequestInfo requestInfo) {
        String url = requestInfo.getUrl().toString();

        try {
            API_URL = new URL(this.jPanelMain.getScanText());
        } catch (MalformedURLException e) {
            STDERR.println(e.getMessage());
        }

        String raw = callbacks.getHelpers().base64Encode(messageInfo.getRequest());
        String data = String.format("uid=%s&url=%s&raw=%s",
                callbacks.getHelpers().urlEncode(UNIQUE_UID), callbacks.getHelpers().urlEncode(url),
                callbacks.getHelpers().urlEncode(raw));
        HttpURLConnection connection = null;
        try {
            connection = (HttpURLConnection) API_URL.openConnection();
            connection.setDoOutput(true);
            connection.setRequestMethod("POST");
            OutputStream outputStream = connection.getOutputStream();
            outputStream.write(data.getBytes());
            outputStream.close();

            BufferedReader reader = new BufferedReader(new InputStreamReader(connection.getInputStream()));
            String msg = reader.readLine();

            if (connection.getResponseCode() != 200) {
                STDERR.println(String.format("%s -> %d\n\t%s\n", url,
                        connection.getResponseCode(), msg));
            } else {
                JSONObject jsonObject = JSON.parseObject(msg);
                if (!"success".equals(jsonObject.getString("flag"))) {
                    String d = jsonObject.getString("data");
                    if (d != null && d.contains("identify")) {  // 身份失效，重新认证
                        STDERR.println(UNIQUE_NAME + " 已失效，请重新认证~");
                        UNIQUE_UID = null;
                        UNIQUE_NAME = null;
                        jPanelMain.setNameLabel("你好~");
                    }
                }
            }
        } catch (IOException e) {
            STDERR.println(e.getMessage());
        } finally {
            if (connection != null) {
                try {
                    connection.getInputStream().close();
                    connection.disconnect();
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }
        }
    }

    /**
     * 认证
     *
     * @param messageInfo
     */
    private void identify(IHttpRequestResponse messageInfo) {
        String host = messageInfo.getHttpService().getHost();
        if(AC_SERVER.contains(host)){ // 认证站点
            IRequestInfo requestInfo = this.callbacks.getHelpers().analyzeRequest(messageInfo.getRequest());

            if (requestInfo.getHeaders().get(0).contains("/api/identify")) {  // 从这个路径下获取认证信息
                IResponseInfo responseInfo = this.callbacks.getHelpers().analyzeResponse(messageInfo.getResponse());
                if (responseInfo.getStatusCode() == 200) {
                    String body = new String(messageInfo.getResponse(), responseInfo.getBodyOffset(),
                            messageInfo.getResponse().length - responseInfo.getBodyOffset());
                    JSONObject jsonObject = JSON.parseObject(body);

                    if (!"success".equals(jsonObject.getString("flag"))) {
                        STDERR.println("认证失败: " + jsonObject.get("data").toString());
                    } else {
                        JSONArray datas = jsonObject.getJSONArray("data");
                        if (datas.size() != 2) {
                            STDERR.println("认证异常！");
                        } else {
                            UNIQUE_NAME = datas.getString(0);
                            UNIQUE_UID = datas.getString(1);
                            STDOUT.println(String.format("%s login ...", UNIQUE_NAME));
                            jPanelMain.setNameLabel(String.format("你好：%s", UNIQUE_NAME));

                            // 认证成功后，重定向到主页
                            messageInfo.setResponse(genRedirectACSite());
                        }
                    }
                }
            }
        } else if (!Utils.identifyWriteList(host)) {
            messageInfo.setResponse(genRedirectAC());  // 不在白名单内重定向到AC
        }
    }

    @Override
    public String getTabCaption() {
        return TAB_CAPTION;
    }

    @Override
    public Component getUiComponent() {
        return jPanelMain;
    }

}
