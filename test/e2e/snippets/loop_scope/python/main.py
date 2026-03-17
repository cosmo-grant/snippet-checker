closures = []

for i in range(3):
    closures.append(lambda: i)

print(closures[0]())
print(closures[1]())
print(closures[2]())
