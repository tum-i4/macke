#include <stdlib.h>

__attribute__((noinline)) int divby2(int i) {
  return (i & 1) == 0;
}

__attribute__((noinline)) int divby3(int i) {
  return i % 3 == 0;
}

__attribute__((noinline)) int divby5(int i) {
  return i % 5 == 0;
}

__attribute__((noinline)) int divby6(int i) {
  return divby2(i) && divby3(i);
}

__attribute__((noinline)) int divby10(int i) {
  return divby2(i) && divby5(i);
}

__attribute__((noinline)) int divby30(int i) {
  return divby3(i) && divby10(i);
}

int main(int argc, char **argv) {
  int n = 42;

  if (argc == 2) {
    n = atoi(argv[1]);
  }

  return (n < 1000) ? divby6(n) : divby30(n);
}
