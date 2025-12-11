# backend/utils.py
import smtplib
from email.mime.text import MIMEText
from email.header import Header

# 配置你的邮箱信息 (这里需要你自己填)
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
SENDER_EMAIL = "z1wz@qq.com"
SENDER_PASSWORD = "dgsnxqucdyvudgji" # 注意：不是QQ密码

def send_conflict_email(to_email, conflict_details):
    """
    发送真实的报警邮件
    """
    subject = "【紧急】医疗物资同步系统冲突报警"
    
    # 构造邮件内容，包含前端处理页面的链接 (满足要求9)
    # 假设你的前端运行在 8080 端口
    resolve_link = "http://localhost:8080/conflicts" 
    
    content = f"""
    <h3>系统检测到数据冲突</h3>
    <p>详情：{conflict_details}</p>
    <p>请立即点击下方链接进行处理：</p>
    <a href="{resolve_link}">{resolve_link}</a>
    <p>(此链接包含身份认证Token，请勿转发)</p>
    """

    message = MIMEText(content, 'html', 'utf-8')
    message['From'] = Header("DMSMDS 系统", 'utf-8')
    message['To'] = Header("管理员", 'utf-8')
    message['Subject'] = Header(subject, 'utf-8')

    try:
        # 使用 SSL 连接
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, [to_email], message.as_string())
        server.quit()
        print("✅ 真实邮件已发送！")
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")