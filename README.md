# Bluetooth Device Triggers

Simple Python utility that uses the scan functionality of `bluetoothctl` to
trigger actions on a Linux machine based on nearby Bluetooth devices.

### Requirements and Installation

This tool assumes your system meets the following requirements:

* `python >= 3.11`
* Linux
* `bluetoothctl` is installed (on my Arch system, this is provided by `bluez-utils`)
* You have a Bluetooth adapter

If those are met, this tool can be installed into a virtual environment with:

```bash
pip install btdtrigger
```

An alternative to manually dealing with virtual environments is to 
use `uv`'s tool interface:

```bash
uv tool install btdtrigger
```

Which allows the utility to be used by prepending `uv tool run`:

```bash
uv tool run btdtrigger --help
```

### Usage

The basic idea of this utility is that it may be useful to have a Linux device
do _something_ when a particular Bluetooth device is seen. The initial
inspiration for this was wanting a gaming PC to turn on remotely when a
Bluetooth controller was powered on. Extending this to arbitrary commands is
straightforward, so that is what we have here.

First, a simple example:

```bash 
btdtrigger run-trigger --address 'AA:BB:CC:DD:EE:FF' --status 'NEW' --command 'echo hello world!'
```

The above command defines a "trigger" which has two conditions and a command.
The conditions are a mac address regex pattern and a device status. If those
conditions are met, the specified command is run. So the above trigger will
listen for a device with mac address `AA:BB:CC:DD:EE:FF` that has the "NEW"
status, which should happen if that device is powered on and searches for a
connection. If those conditions are met, "hello world!" should be printed to
the terminal.

#### Conditions: mac address patterns and status

Each trigger must match two conditions: a regex pattern for the device
mac address, `address`, and a specified `status`. The address pattern 
can be any valid regex (and will ignore case). Some examples are:

* `'.*'` - match any address
* `'AA:BB:CC:DD:EE:FF'` - matches this mac address exactly
* `'AA.*'` - matches any mac address starting with `AA`
* `'AA:BB:CC:DD:EE:FF|11:22:33:44:55:66'` - matches either of the given mac addresses

The `status` is simpler, it must be one of the following:

* `'NEW'` - this status occurs when the listener sees a device that it didn't
previously see (it is added to the list of devices in `bluetoothctl`)
* `'DEL'` - this status occurs when a device previously in the list is no longer
detectable, often from turning off or successfully connecting to another device
and no longer advertising

So triggers that you want to run when a device is turned on, for example, 
would use the `'NEW'` status. If you want the opposite behavior, where the trigger
runs when no longer seen, you could use the `'DEL'` status.

#### Commands and templates

The command to be run should be a valid shell command that can be run by the
owner of the `btdtrigger` process. Under the hood it will be run as a `subprocess.run`,
so the trigger listener process will wait for the command to complete before
continuing to listen or run any other triggered commands.

Commands also support very limited _templates_, where attributes of the
trigger or device can be injected into the command themselves. The following
templates are supported:

* `%address%` - The mac address of the matched Bluetooth device
* `%name%` - The advertised name of the Bluetooth device
* `%status%` - The status condition of the trigger

For example, the following trigger definition will include the triggering
devices mac address in the command in place of the `%address%` template
and run against every new device seen.

```bash 
btdtrigger run-trigger --address '.*' --status 'NEW' --command 'echo device %address% is new'
```

### Running multiple triggers via a configuration file

In addition to the `btdtrigger run-trigger` command, where you define your trigger 
directly in the command itself, you can use the `btdtrigger run` command
to execute triggers defined in a `config.toml` file as below:

```toml
[[triggers]]
device = ".*"
status = "NEW"
command = "echo device %address% is new"
```

This defines an identical trigger as used in the previous section and can be run with:

```bash
btdtrigger run -c config.toml
```

If a file is not provided via the `-c` option, it will default to `~/.config/btdtrigger/config.toml`.

One benefit of defining triggers in a configuration file is the ability define
multiple triggers together, which can be done by adding a new `[[triggers]]`
block. We can update our `config.toml` to be:

```toml
[[triggers]]
device = ".*"
status = "NEW"
command = "echo device %address% is new"

[[triggers]]
device = ".*"
status = "DEL"
command = "echo device %address% is lost"
```

Running this should now echo out all the devices being seen and lost by the
Bluetooth scan.
