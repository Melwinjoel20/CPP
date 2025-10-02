class Welcome:
    def __init__(self, name):   
        self.full_name = name

    def greet(self):
        return 'Hello {}'.format(self.full_name)
