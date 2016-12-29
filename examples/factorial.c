
unsigned int fac(unsigned int n) {
  return (n > 1) ? n * fac(n - 1) : 1;
}
