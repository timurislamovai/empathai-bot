{\rtf1\ansi\ansicpg1251\cocoartf2511
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww10800\viewh8400\viewkind0
\pard\tx566\tx1133\tx1700\tx2267\tx2834\tx3401\tx3968\tx4535\tx5102\tx5669\tx6236\tx6803\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import json\
import os\
\
# \uc0\u1047 \u1072 \u1075 \u1088 \u1091 \u1079 \u1082 \u1072  \u1090 \u1077 \u1082 \u1089 \u1090 \u1072  \u1080 \u1079  \u1092 \u1072 \u1081 \u1083 \u1072 \
def load_text(filename):\
    filepath = os.path.join("texts", f"\{filename\}.txt")\
    if os.path.exists(filepath):\
        with open(filepath, "r", encoding="utf-8") as f:\
            return f.read()\
    return "\uc0\u1060 \u1072 \u1081 \u1083  \u1085 \u1077  \u1085 \u1072 \u1081 \u1076 \u1077 \u1085 ."\
\
# \uc0\u1056 \u1072 \u1073 \u1086 \u1090 \u1072  \u1089  \u1087 \u1086 \u1083 \u1100 \u1079 \u1086 \u1074 \u1072 \u1090 \u1077 \u1083 \u1103 \u1084 \u1080  (\u1095 \u1077 \u1088 \u1077 \u1079  \u1083 \u1086 \u1082 \u1072 \u1083 \u1100 \u1085 \u1099 \u1081  users.json \u1080 \u1083 \u1080  JSONBin)\
USER_DATA_FILE = "users.json"\
\
def load_user_data():\
    if os.path.exists(USER_DATA_FILE):\
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:\
            return json.load(f)\
    return \{\}\
\
def save_user_data(data):\
    with open(USER_DATA_FILE, "w", encoding="utf-8") as f:\
        json.dump(data, f, ensure_ascii=False, indent=2)\
}