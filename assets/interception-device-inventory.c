#include <stdio.h>
#include <wchar.h>
#include "interception.h"

int main(void)
{
    InterceptionContext context = interception_create_context();
    if (!context) {
        fputs("Cannot open an Interception context. Check the driver, elevation and edition.\n", stderr);
        return 1;
    }

    unsigned int count = 0;
    for (InterceptionDevice device = 1; device <= INTERCEPTION_MAX_DEVICE; ++device) {
        wchar_t hardware_id[512] = {0};
        unsigned int bytes = interception_get_hardware_id(
            context, device, hardware_id, (unsigned int)sizeof hardware_id);
        if (bytes == 0) {
            continue;
        }
        hardware_id[(sizeof hardware_id / sizeof hardware_id[0]) - 1] = L'\0';
        wprintf(L"%ls %d: %ls\n", interception_is_keyboard(device) ? L"Keyboard" : L"Mouse",
                device, hardware_id);
        ++count;
    }

    interception_destroy_context(context);
    if (count == 0) {
        fputws(L"No hardware IDs were returned for this context.\n", stdout);
        return 2;
    }
    return 0;
}
