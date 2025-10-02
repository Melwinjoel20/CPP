class shop():
    def __init__(self, caps, shirt, hoodies):
        self.caps = caps
        self.shirt = shirt
        self.hoodies = hoodies
        self.total = 0

    def fn_caps(self):
        a_cap = 5
        return a_cap * self.caps

    def fn_shirt(self):
        a_shirt = 20
        return a_shirt * self.shirt

    def fn_hoodie(self):
        a_hoodie = 20
        return a_hoodie * self.hoodies
    def grand_total(self):
        return self.fn_caps()+self.fn_shirt()+self.fn_hoodie()
