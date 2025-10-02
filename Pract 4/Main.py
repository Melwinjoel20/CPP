class job():
    def __init__(self, no_job, basic_pay, hours_per_week, overtime_per_week):
        self.job_name = no_job
        self.basic_pay = basic_pay
        self.hours_per_week = hours_per_week
        self.overtime_per_week = overtime_per_week

    def bob(self):
        basic = self.basic_pay * self.hours_per_week
        ot = self.overtime_per_week * (self.basic_pay * 1.5)

        return basic + ot
        #return "The basic pay of bob: {}\nThe overtime pay of BOB: {}\nTotal Pay = {}". format(basic, ot, total)
    
    def details(self):
        basic = self.basic_pay * self.hours_per_week
        ot = self.overtime_per_week * (self.basic_pay * 1.5)
        total = self.bob()
        return "Job: {}\nBasic Pay: {}\nOvertime Pay: {}\nTotal Pay = {}".format(self.job_name, basic, ot, total)
        
