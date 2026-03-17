package main

import "fmt"

func main() {
	closures := make([]func() int, 0)
	for i := 0; i < 3; i++ {
		closures = append(closures, func() int { return i })
	}
	fmt.Println(closures[0]())
	fmt.Println(closures[1]())
	fmt.Println(closures[2]())
}
