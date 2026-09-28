# Running on a VPS

Run development, dependencies, tests, and the MCP server on your VPS. SSH carries MCP
stdio; use `ssh -T` (no pseudo-terminal) so binary/image JSON is not altered.
The remote login must be non-interactive, and shell startup must not print to stdout.

ADB must see a device from that same host. Options:

- Run an Android emulator on the VPS. Hardware virtualization makes this much faster;
  software emulation is useful for smoke tests but slow.
- Pair a device over a trusted private network following the official
  [wireless debugging instructions](https://developer.android.com/tools/adb#wireless).
  A phone on your home Wi-Fi is not automatically reachable from AWS.
- If ADB already runs on a computer with a USB phone, explicitly forward its loopback
  ADB server through SSH. This requires ADB on that computer; it is not part of the
  AWS-only build workflow. For example, from the USB host:

  ```sh
  adb start-server
  ssh -N -R 127.0.0.1:15037:127.0.0.1:5037 YOUR_VPS_SSH_ALIAS
  ```

  Then set `ADB_SERVER_SOCKET=tcp:127.0.0.1:15037` for phone-use on the VPS. Use compatible
  ADB versions on both hosts, and close the tunnel when finished. This gives the VPS
  access to the devices authorized by that ADB server. Validate with `adb devices -l`
  under the same environment before starting phone-use.

Do not expose ADB or an unauthenticated MCP service to the public internet. phone-use
only offers stdio; it does not open a network listener or change AWS firewall rules.
