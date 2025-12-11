#include <stdio.h>
#include <stdlib.h>

int main() {
    int a, b, c;
    printf("Enter 3 digits: ");
    scanf("%d %d %d", &a, &b, &c);
    if (a > b && a > c) {
        printf("Largest number: %d\n", a);
        exit(0);
    }
    else if (b > a && b > c) {
        printf("Largest number: %d\n", b);
        exit(0);
    }
    else if (c > a && c > b) {
        printf("Largest number is: %d\n", c);
        exit(0);
    }
    else {
        printf("Something is wrong with you!!\n");
    }
    return 0;
}