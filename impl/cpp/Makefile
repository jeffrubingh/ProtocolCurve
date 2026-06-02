CXX ?= c++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra
BOOK = ../../examples/fixtures/book.txt

.PHONY: all run test clean

all: parity

parity: parity.cpp
	$(CXX) $(CXXFLAGS) -o parity parity.cpp

run: parity
	./parity $(BOOK)

test: parity
	./parity --self-test

clean:
	rm -f parity
