package frame;

import burp.BurpExtender;
import flow.Utils;
import jdk.nashorn.internal.scripts.JO;

import javax.swing.*;

public class MainPanel extends JPanel {

    private JLabel nameLabel;  // 标签
    private JTextField parseText = null;


    /**
     * 获取解析服务器的地址
     *
     * @return
     */
    public String getScanText() {
        return parseText == null ? "null" : parseText.getText();
    }

    public static void main(String[] args) {
        BurpExtender.AC_SERVER = JOptionPane.showInputDialog(null, "请输入服务器地址：", "http://127.0.0.1");

        JFrame frame = new JFrame("test frame");
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setSize(500, 500);

        JPanel jPanel = new MainPanel();
        frame.add(jPanel);
        frame.setVisible(true);
    }

    public MainPanel() {
        this.setLayout(null);

        nameLabel = new JLabel("你好~");
        nameLabel.setBounds(10, 20, 400, 25);
        this.add(nameLabel);

        flowParse();
    }

    private void flowParse() {
        JLabel jLabel = new JLabel("流量解析服务器：");
        jLabel.setBounds(10, 80, 140, 25);
        this.add(jLabel);

        parseText = new JTextField(20);
        parseText.setBounds(140, 80, 350, 25);
        parseText.setText(BurpExtender.AC_SERVER + "/api/parse");
        parseText.setEnabled(false);
        this.add(parseText);

        JButton doButton = new JButton("开始扫描");
        doButton.setBounds(10, 120, 120, 25);
        doButton.addActionListener((e) -> {
            if (BurpExtender.UNIQUE_NAME == null) {
                JOptionPane.showMessageDialog(null,
                        "请先在浏览器中登陆！", "提示", JOptionPane.ERROR_MESSAGE);
                return;
            }

            BurpExtender.SCAN_FLAG = !BurpExtender.SCAN_FLAG;
            if (BurpExtender.SCAN_FLAG) {  // 扫描任务开启
                BurpExtender.STDOUT.println(String.format("[+] %s start scanning ...", BurpExtender.UNIQUE_NAME));
                doButton.setText("停止扫描");
            } else {
                BurpExtender.STDOUT.println("[-] stop scanning ...\r\n");
                doButton.setText("开始扫描");
            }
        });
        this.add(doButton);
    }

    /**
     * 设置nameLabel标签
     *
     * @param name
     */
    public void setNameLabel(String name) {
        if (nameLabel != null) {
            nameLabel.setText(name);
        }
    }
}
