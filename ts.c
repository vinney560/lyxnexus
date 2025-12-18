#include <stdio.h>
#include <stdlib.h>
int x, y;
int sum() {
    // Get two nums and sum them
    int x, y;
    printf("=== Do sum ===\n");
    printf("Enter first number: ");
    scanf("%d", &x);
    printf("Enter second number: ");
    scanf("%d", &y);
    int added = x + y;
    printf("Sum: %d\n", added);
    return sum();
}
int subtract() {
    // Get two nums and subtract them
    int x, y;
    printf("=== Do subtraction ===\n");
    printf("Enter first number: ");
    scanf("%d", &x);
    printf("Enter second number: ");
    scanf("%d", &y);
    int sub = x - y;
    printf("Subtracted: %d\n", sub);
    return subtract();
}
int multiply() {
    // Get two nums and multiple
    int x, y;
    printf("=== Do Multiplication ===\n");
    printf("Enter first number: ");
    scanf("%d", &x);
    printf("Enter second number: ");
    scanf("%d", &y);
    int mul = x * y;
    printf("Multiplied: %d\n", mul);
    return multiply();
}
int division() {
    // Get two nums and divide
    float x, y;
    printf("=== Do Division ===\n");
    printf("Enter first number: ");
    scanf("%f", &x);
    printf("Enter second number: ");
    scanf("%f", &y);
    if (x != 0) {
        float div = x * y;
        printf("Division: %.2f\n", div);
    }
    else {
        printf("Can not divide with Zero\n");
    }
    return division();
}

int main() {
    int choice;
    printf("==============\n");
    printf("1. Sum\n");
    printf("2. Subtract\n");
    printf("3. Multiply\n");
    printf("4. Division\n");
    printf("==============\n");
    printf("Choose ops: ");
    scanf("%d", &choice);
    switch(choice) {
        case 1:
            return sum();
        case 2:
            return subtract();
        case 3:
            return multiply();
        case 4:
            return division();
        default:
            printf("Invalid choice\n");
            exit(0);
    }
    return 0;
}