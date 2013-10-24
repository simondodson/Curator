import os
count = 0
for name in os.listdir(os.getcwd()):
    if name.endswith('.py'):
        data = open(name, 'r').readlines()
        count += len(data)
        print(name, len(data))

print('TOTAL =', count)