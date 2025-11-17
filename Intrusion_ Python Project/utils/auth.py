import os

def is_logged_in():
    flag_file = "temp_flags/.logged_in"
    if os.path.exists(flag_file):
        with open(flag_file, "r") as f:
            if f.read().strip() == "true":
                return True
            
    return False