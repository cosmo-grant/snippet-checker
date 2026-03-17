const closures = [];

for (let i = 0; i < 3; i++) {
  closures.push(function () {
    console.log(i);
  });
}

closures[0]();
closures[1]();
closures[2]();
