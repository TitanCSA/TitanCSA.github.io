param(
    [Parameter(Mandatory)]
    [ValidateSet('Interceptor','InterceptorKeyboardMouse','InterceptorGamepadController','Vdevice','InterceptionV2')]
    [string]$Module
)

$ErrorActionPreference = 'Stop'
Import-Module -Name $Module -RequiredVersion 1.0.0
$client = & "Connect-${Module}SDK"
try {
    switch ($Module) {
        Vdevice { Invoke-VdeviceSDK -Client $client -Operation status }
        InterceptionV2 { Invoke-InterceptionV2SDK -Client $client -Operation check -Arguments @{ device = 1 } }
        default { & "Get-${Module}SDKInfo" -Client $client }
    }
} finally {
    & "Disconnect-${Module}SDK" -Client $client
}
