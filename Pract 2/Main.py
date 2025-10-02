class user_details():
    def __init__(self, age, height):
        self.age = age
        self.height = height
    
    def weight(self):
        RW = (self.height - 100 + self.age % 10) * 0.90
        return "Your weight is:{}".format(RW)
