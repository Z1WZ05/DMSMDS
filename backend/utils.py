# backend/utils.py 完整修复版
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr # 【新增】用于格式化标准地址
from .config import settings

def send_conflict_email(table_name, record_id, reason):
    """
    发送冲突报警邮件 (修复 RFC5322 合规性问题)
    """
    if not settings.SENDER_EMAIL or not settings.SMTP_PASSWORD:
        print("⚠️ 邮件发送失败：管理员尚未在设置面板配置邮箱或授权码")
        return

    subject = "【系统预警】分布式医疗系统数据冲突通知"
    login_url = f"{settings.FRONTEND_URL}/login"
    
    content = f"""
    <h3>管理员您好：</h3>
    <p>系统在自动同步过程中检测到数据冲突，相关记录已被锁定，需人工干预。</p>
    <table border="1" cellspacing="0" cellpadding="5">
        <tr><td><b>涉及表</b></td><td>{table_name}</td></tr>
        <tr><td><b>记录ID</b></td><td>{record_id}</td></tr>
        <tr><td><b>冲突原因</b></td><td>{reason}</td></tr>
    </table>
    <p>请点击下方链接登录系统进行处理：</p>
    <a href="{login_url}">{login_url}</a>
    <br>
    <p>此邮件为系统自动发送，请勿回复。</p>
    """

    message = MIMEText(content, 'html', 'utf-8')
    
    # 【核心修复点】
    # 必须符合 "Display Name <email@domain.com>" 格式
    # 且 email 部分必须和 settings.SENDER_EMAIL 一致
    message['From'] = formataddr((str(Header("医疗系统监控中心", 'utf-8')), settings.SENDER_EMAIL))
    message['To'] = formataddr((str(Header("系统管理员", 'utf-8')), settings.SENDER_EMAIL))
    
    message['Subject'] = Header(subject, 'utf-8')

    try:
        # 使用 SSL 连接
        server = smtplib.SMTP_SSL(settings.SMTP_SERVER, settings.SMTP_PORT)
        # 这里的 login 账号必须和 message['From'] 里的邮箱地址一致
        server.login(settings.SENDER_EMAIL, settings.SMTP_PASSWORD)
        
        # 发送邮件
        # sendmail(发件人, [收件人列表], 邮件字符串)
        server.sendmail(settings.SENDER_EMAIL, [settings.SENDER_EMAIL], message.as_string())
        server.quit()
        print(f"✅ 邮件已成功发送至 {settings.SENDER_EMAIL}")
    except Exception as e:
        print(f"❌ 邮件发送出错: {str(e)}")