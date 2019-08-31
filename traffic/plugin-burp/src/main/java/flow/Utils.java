package flow;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class Utils {
    /**
     * 根据后缀筛选流量
     *
     * @param ext
     * @return
     */
    public static boolean filterFlowByExt(String ext) {
        ext = ext.toLowerCase();
        String[] filterExt = {"jpg", "png", "js", "css", "ico", "gif", "svg", "font"};
        for (String f : filterExt) {
            if (ext.endsWith(f)) {
                return true;
            }
        }
        return false;
    }

    /**
     * 根据path生成后缀
     *
     * @param path
     * @return
     */
    public static String genExt(String path) {
        int dot = path.lastIndexOf('.');
        int slash = path.lastIndexOf('/');

        if (dot == -1 || dot < slash) {  // 没有. 或者 斜杠后没有·，没有后缀
            return "";
        }

        return path.substring(dot);
    }

    /**
     * 获取url中的host
     *
     * @param url
     * @return
     */
    public static String genHost(String url) {
        if (url == null) {
            return "";
        }
        Pattern urlPattern = Pattern.compile("^http[s]?://(?<host>[\\w.:]+)");
        Matcher matcher = urlPattern.matcher(url);
        if (matcher.find()) {
            return matcher.group("host");
        }
        return "";
    }

    /**
     * 未认证时的host白名单
     *
     * @param host
     * @return
     */
    public static boolean identifyWriteList(String host) {
        return host.startsWith("127.0.0.1") || host.startsWith("localhost");
    }

    /**
     * 根据host筛选流量
     *
     * @param host
     * @return
     */
    public static boolean filterFlowByHost(String host) {
        int colon = host.indexOf(':');
        if (colon != -1) {
            host = host.substring(0, colon);  // 取前半部分
        }
        host = host.toLowerCase();
        // 直接收ip，不接受域名
        // 有需要可以自己修改
        Pattern pattern = Pattern.compile("\\d+\\.\\d+\\.\\d+\\.\\d+");
        return !pattern.matcher(host).find();
    }


    public static void main(String[] args) {
        String url = "http://127.0.0.1/api/parse";
        System.out.println(genHost(url));
    }
}
