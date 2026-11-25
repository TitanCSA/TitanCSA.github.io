'use strict';

// Save this file in the app folder where you ran npm install.
const packages = new Map([
  ['interceptor', 'interceptor-sdk'],
  ['interceptor-keyboard-mouse', 'interceptor-keyboard-mouse-sdk'],
  ['interceptor-gamepad-controller', 'interceptor-gamepad-controller'],
]);
const packageName = packages.get(process.argv[2]);
if (!packageName) {
  console.error('Choose an edition: ' + [...packages.keys()].join(', '));
  process.exitCode = 1;
} else {
  let client;
  try {
    const { Interceptor } = require(packageName);
    client = new Interceptor();
    const status = client.info();
    console.log(JSON.stringify(status, null, 2));
  } catch (error) {
    if (error.code === 2) {
      console.error('Windows 2. Run InterceptorSetup.exe from the demo for ' + process.argv[2] + '.');
      process.exitCode = 2;
    } else {
      console.error(error.message);
      process.exitCode = 1;
    }
  } finally {
    if (client) client.close();
  }
}
