/* First library check for Interception V2. No driver or context required. */
#include "interception.h"

#include <stdio.h>

int main(void)
{
    unsigned keyboards = 0;
    unsigned mice = 0;
    for (InterceptionDevice slot = 1; slot <= INTERCEPTION_MAX_DEVICE; ++slot) {
        keyboards += interception_is_keyboard(slot) != 0;
        mice += interception_is_mouse(slot) != 0;
    }
    if (keyboards != INTERCEPTION_MAX_KEYBOARD || mice != INTERCEPTION_MAX_MOUSE) {
        fputs("Unexpected slot ranges. Check that the DLL matches the SDK.\n", stderr);
        return 1;
    }
    printf("Library loaded. Keyboard slots: %u; mouse slots: %u.\n", keyboards, mice);
    return 0;
}
