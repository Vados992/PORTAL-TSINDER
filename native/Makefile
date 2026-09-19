CXX ?= c++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra -Werror

.PHONY: all clean
all: ../build/portal-guard

../build/portal-guard: guard.cpp
	mkdir -p ../build
	$(CXX) $(CXXFLAGS) $< -o $@

clean:
	rm -f ../build/portal-guard
