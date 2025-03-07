'''
Author: wanghaitao
Date: 2024-05-30 21:07:24
LastEditTime: 2024-05-31 09:57:27
LastEditors: wanghaitao
Description: 
Copyright (c) 2024 by Cosmartor, All Rights Reserved. 
'''
import ctypes
from ctypes import POINTER, c_ubyte, c_uint, c_char_p, byref
import os
from enum import Enum

class CKeyGenResultEx(Enum):
    KGRE_Ok = 0
    KGRE_BufferToSmall = 1
    KGRE_SecurityLevelInvalid = 2
    KGRE_VariantInvalid = 3
    KGRE_UnspecifiedError = 4
    
class CKeyGenerator:
    def __init__(self, dll_path):
        if not os.path.isfile(dll_path):
            raise FileNotFoundError(f"Cannot find DLL at {dll_path}")

        self.dll = ctypes.CDLL(dll_path)
        self._setup_function_prototype()

    def _setup_function_prototype(self):
        self.GenerateKeyEx = self.dll.GenerateKeyEx
        self.GenerateKeyEx.argtypes = [
            POINTER(c_ubyte),  # iSeedArray
            c_uint,  # iSeedArraySize
            c_uint,  # iSecurityLevel
            c_char_p,  # iVariant
            POINTER(c_ubyte),  # ioKeyArray
            c_uint,  # iKeyArraySize
            POINTER(c_uint)  # oSize
        ]
        self.GenerateKeyEx.restype = c_uint  # 返回值是枚举类型的值

    def generate_key(self, seed_array, security_level, variant, key_array_size):
        seed_array = (c_ubyte * len(seed_array))(*seed_array)
        key_array = (c_ubyte * key_array_size)()
        actual_key_size = c_uint()

        result_code = self.GenerateKeyEx(
            seed_array,
            len(seed_array),
            security_level,
            variant.encode('utf-8'),  # 确保变体字符串是字节字符串
            key_array,
            key_array_size,
            byref(actual_key_size)
        )

        result = CKeyGenResultEx(result_code)
        actual_key = list(key_array)[:actual_key_size.value]
        return result, actual_key_size.value, actual_key