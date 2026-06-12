import math

def calculate_reading_time(text: str):
    words = len(text.split())
    minutes = math.ceil(words / 200)
    return minutes