#include <assert.h>

int f2(int i) {
  assert(i != 2);
  return i;
}

int f3(int i) {
  assert(i % 3 == 0);
  assert(i % 5 == 0);
  return i;
}

int f1(int i) {
  if (i % 2 == 0) {
    return f2(i);
  } else {
    return f3(i);
  }
}
