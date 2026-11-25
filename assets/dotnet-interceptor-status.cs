// SPDX-License-Identifier: MIT
using System;
using System.Text.Json;
using TitanCSA.Interceptor;

try
{
    using var client = new Interceptor();
    var info = client.GetInfo();
    Console.WriteLine(JsonSerializer.Serialize(new
    {
        installed = info.Installed,
        active = info.Active,
        trial_state = info.TrialState,
    }));
    return 0;
}
catch (InterceptorException error) when (error.Code == 2)
{
    Console.Error.WriteLine(error.Message);
    return 2;
}
