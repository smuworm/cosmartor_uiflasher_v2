import winreg

# 示例使用
g_sub_key = r"Software\cosmartor\FlashSeqEditor"
g_value_name = "path"

# 创建或打开一个键
def reg_create_or_open_key(sub_key, access=winreg.KEY_ALL_ACCESS):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key, 0, access)
    except FileNotFoundError:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub_key)
    return key
 
# 关闭键
def reg_close_key(key):
    winreg.CloseKey(key)
 
# 读取键值
def reg_read_value(sub_key, value_name):
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key)
    try:
        value, type = winreg.QueryValueEx(key, value_name)
    except FileNotFoundError:
        value = None
    finally:
        winreg.CloseKey(key)
    return value
 
# 写入键值
def reg_write_value(sub_key, value_name, value_data):
    key = reg_create_or_open_key(sub_key)
    winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, value_data)
    winreg.CloseKey(key)
 
# 判断键值是否存在
def reg_does_value_exist(sub_key, value_name):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key)
        try:
            winreg.QueryValueEx(key, value_name)
            value_exists = True
        except FileNotFoundError:
            value_exists = False
        finally:
            winreg.CloseKey(key)
        return value_exists
    except:
       return False

# # 创建或打开键
# key = create_or_open_key(sub_key)
 
# # 写入键值
# write_value(sub_key, value_name, "Hello, World!")
 
# # 读取键值
# value = read_value(sub_key, value_name)
# print(value)  # 输出: Hello, World!
 
# # 判断键值是否存在
# exists = does_value_exist(sub_key, value_name)
# print(exists)  # 输出: True
 
# # 关闭键
# close_key(key)
# 请注意