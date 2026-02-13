import sys
import os

# 添加项目根目录到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.memory.MySQL_Abstractor import MySQLAbstractor

user_id = "user_123"
session_id = "session_456"

def test_mysql_abstractor():
    mysql_abstractor = MySQLAbstractor(
        db_url="mysql+pymysql://root:123456@localhost:3306/video_agent",
    )
    result =mysql_abstractor.check_threshold(user_id, session_id, threshold=40)
    
    if result:
        mysql_abstractor.update_with_abstract(user_id, session_id)
        mysql_abstractor.close()
    else:
        print("累计token使用量未超过阈值，不需要摘要")
        mysql_abstractor.close()

if __name__ == "__main__":
    test_mysql_abstractor()

