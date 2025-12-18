#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdlib.h>
#include <klee/klee.h>
#include <stdio.h>

// A regular expression operation.
typedef enum { OR, SEQ, STAR, RANGE } RegexOp;

// A regular expression AST node.
typedef struct Regex Regex;
struct Regex {
    RegexOp op;
    int clo;
    int chi;
    Regex* left;
    Regex* right;
};

// A regular expression continuation as a linked list
// of regular expressions in a list to be matched.
typedef struct RegexCont RegexCont;
struct RegexCont {
    Regex* regex;
    RegexCont* next;
};

// Match a regular expression against a string with a continuation.
static int match_cont(Regex* regex, RegexCont* cont, char *text) {
  // If the regex is null (empty) then return true only if the string is over.
  if (regex == NULL) {
    return *text == '\0';
  }
  // Regex OR, check both sides.
  if (regex->op == OR) {
    return match_cont(regex->left, cont, text) || match_cont(regex->right, cont, text);
  }
  // Regex SEQ, check the first and pass the second as a continuation.
  if (regex->op == SEQ) {
    RegexCont c;
    c.next = cont;
    c.regex = regex->right;
    return match_cont(regex->left, &c, text);
  }
  // Regex STAR, case for iteration.
  if (regex->op == STAR) {
    Regex r;
    r.op = SEQ;
    r.left = regex->left;
    r.right = regex;
    return match_cont(cont->regex, cont->next, text) || (*text != '\0' && match_cont(&r, cont, text));
  }
  // Regex RANGE, base case check match and continue to continuation.
  if (regex->op == RANGE) {
    char c = *text++;
    return c != '\0' && c >= regex->clo && c <= regex->chi && match_cont(cont->regex, cont->next, text);
  }

  return 0;
}

// Match a regular expression against a string.
static int match(Regex* regex, char *text) {
    RegexCont cont;
    cont.next = NULL;
    cont.regex = NULL;
    return match_cont(regex, &cont, text);
}




bool isValidDomainName(char* domain_name) {
    Regex r0;
    r0.op = RANGE;
    r0.clo = 97;
    r0.chi = 122;
    Regex r1;
    r1.op = RANGE;
    r1.clo = 42;
    r1.chi = 42;
    Regex r2;
    r2.op = OR;
    r2.left = &r0;
    r2.right = &r1;
    Regex r3;
    r3.op = RANGE;
    r3.clo = 46;
    r3.chi = 46;
    Regex r4;
    r4.op = RANGE;
    r4.clo = 97;
    r4.chi = 122;
    Regex r5;
    r5.op = RANGE;
    r5.clo = 42;
    r5.chi = 42;
    Regex r6;
    r6.op = OR;
    r6.left = &r4;
    r6.right = &r5;
    Regex r7;
    r7.op = SEQ;
    r7.left = &r3;
    r7.right = &r6;
    Regex r8;
    r8.op = STAR;
    r8.left = &r7;
    Regex r9;
    r9.op = SEQ;
    r9.left = &r2;
    r9.right = &r8;
    return match(&r9, domain_name);
}

bool isValidInputs(char* domain_name, char* ipv4_domain_name) {
    if (domain_name == NULL || ipv4_domain_name == NULL) {
        return false;
    }

    if (!isValidDomainName(domain_name) || !isValidDomainName(ipv4_domain_name)) {
        return false;
    }

    return true;
}

bool is_matching_a_record(char* domain_name, char* ipv4_domain_name) {
    if (strcmp(ipv4_domain_name, "*") == 0) {
        return true;
    }

    char* ptr1 = domain_name + strlen(domain_name) - 1;
    char* ptr2 = ipv4_domain_name + strlen(ipv4_domain_name) - 1;

    while (ptr1 >= domain_name && ptr2 >= ipv4_domain_name) {
        if (*ptr2 == '*') {
            return true;
        }

        if (*ptr1 != *ptr2) {
            return false;
        }

        ptr1--;
        ptr2--;
    }

    if (ptr1 < domain_name && ptr2 >= ipv4_domain_name && *ptr2 != '*') {
        return false;
    }

    if (ptr2 < ipv4_domain_name && ptr1 >= domain_name) {
        return false;
    }

    return true;
}

int main() {
    char x0[6];
    char x1;
    klee_make_symbolic(&x1, sizeof(x1), "x1");
    x0[0] = x1;
    char x2;
    klee_make_symbolic(&x2, sizeof(x2), "x2");
    x0[1] = x2;
    char x3;
    klee_make_symbolic(&x3, sizeof(x3), "x3");
    x0[2] = x3;
    char x4;
    klee_make_symbolic(&x4, sizeof(x4), "x4");
    x0[3] = x4;
    char x5;
    klee_make_symbolic(&x5, sizeof(x5), "x5");
    x0[4] = x5;
    x0[5] = '\0';
    char x6[6];
    char x7;
    klee_make_symbolic(&x7, sizeof(x7), "x7");
    x6[0] = x7;
    char x8;
    klee_make_symbolic(&x8, sizeof(x8), "x8");
    x6[1] = x8;
    char x9;
    klee_make_symbolic(&x9, sizeof(x9), "x9");
    x6[2] = x9;
    char x10;
    klee_make_symbolic(&x10, sizeof(x10), "x10");
    x6[3] = x10;
    char x11;
    klee_make_symbolic(&x11, sizeof(x11), "x11");
    x6[4] = x11;
    x6[5] = '\0';
    bool x12;
    klee_make_symbolic(&x12, sizeof(x12), "x12");
    bool bad_input;
    bool result_tmp;
    bool x13;
    klee_make_symbolic(&x13, sizeof(x13), "x13");
    if(isValidInputs(x0, x6)){
        bad_input = false;
        result_tmp = is_matching_a_record(x0, x6);
    }
    else{
        bad_input = true;
        result_tmp = false;
    }
    klee_assume(result_tmp == x12);
    klee_assume(bad_input == x13);
    return 0;
}