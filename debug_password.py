# debug_password.py
from backend.security import verify_password, get_password_hash, pwd_context

# 1. 模拟输入
plain = "123"

# 2. 【关键】请把数据库里 nurse_1 的 password 字段完整复制粘贴到这里！
# 必须完全一致，不要有空格
db_hash = "$pbkdf2-sha256$29000$D6E0JsQ4h7C21ppTyhmDsA$kNRJoLn5z3ZE6E1uSENoSOkVOHD8uVcElcTKra52GIU" # <--- 请替换这一行！！！

print("="*30)
print(f"输入明文: {plain}")
print(f"数据库存的哈希: {db_hash}")
print("="*30)

# 测试 1: 直接验证
try:
    result = verify_password(plain, db_hash)
    print(f"🔍 测试1 - 数据库哈希验证结果: {result}")
except Exception as e:
    print(f"❌ 测试1 报错: {e}")

# 测试 2: 现场生成现场验证
try:
    new_hash = get_password_hash(plain)
    print(f"🆕 现场新生成的哈希: {new_hash}")
    result_new = verify_password(plain, new_hash)
    print(f"🔍 测试2 - 新生成哈希验证结果: {result_new}")
except Exception as e:
    print(f"❌ 测试2 报错: {e}")

# 查看配置
print("="*30)
print(f"当前加密配置: {pwd_context.to_dict()}")