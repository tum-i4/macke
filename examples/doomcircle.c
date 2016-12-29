__attribute__((noinline)) int a(int n);
__attribute__((noinline)) int b(int n);
__attribute__((noinline)) int c(int n);

int a(int n) {
  return b(n + 1);
}

int b(int n) {
  if (n > 10) {
    return n;
  } else {
    return c(n + 1);
  }
}

int c(int n) {
  return a(n + 1);
}

int main(int argc, char** argv) {
  return a(argc);
}
