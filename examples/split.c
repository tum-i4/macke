#include <assert.h>

void bottom(int i) {
  assert(i < 42);
}

void left(int i) {
  bottom(i);
}

void right(int i) {
  bottom(i);
}

void top(int i) {
  if (i % 2 == 0) {
    left(i);
  } else {
    right(i);
  }
}
