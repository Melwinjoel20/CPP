from Main import job

a_job = int(input ("Enter the number of jobs :"))
best_pay=0
best_job = ""
i=1
while (i <= a_job):
    a_basic_pay = int(input("Enter the Basic Pay:"))
    a_per_week = int(input("Enter the number of hour per week:"))
    a_ot_per_week = int(input("Enter the number of ovetime hour per week:"))

    obj = job("Job{}".format(i), a_basic_pay, a_per_week, a_ot_per_week)
    print(obj.details())

    if obj.bob() > best_pay:
        best_pay = obj.bob()
        best_job = obj 
    i += 1

    print("\nThe best job is {} with total pay {}".format(best_job.job_name, best_pay))

