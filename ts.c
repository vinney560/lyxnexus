#include <stdio.h>

float getValues(void) {
    float x, y;
    printf("Enter first number: ");
    scanf("%f", &x);
    printf("Enter second number: ");
    scanf("%f", &y);
    return x / y;
}
int main() {
    float div = getValues();
    printf("Division: %.2f\n", div);  
    return 0;
}