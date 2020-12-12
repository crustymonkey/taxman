# About
An easily pluggable host level metrics collector.  There are a number of plugins included, but it's quite easy to add your own as well.

# Getting Running with Default Plugins
Your path to getting running is primarily the configuration of your taxman.ini file.  The `[main]` section is where you are going to define the remote receiver and associated username/password.  This works in much the same way as the `collectd` `write_http` plugin.

Beyond that, you want to enable the default plugins you are intested in.  To get it up and running, just run `taxman.py -c path/to/config`.

# Creating Your Own Plugin
First, create a file in `libtaxman/plugins` with a legal Python module name.  For the purposes of these examples, we'll say your plugin file is named `myexample.py`.

## Stubbing Out `myexample.py`
The basics of your plugin are pretty simple:

```
from gdata_subm import Gdata
from libtaxman.collector import BaseCollector
from typing import Union, List

class MyCollector(BaseCollector):
    def get_data_for_sub(self) -> Union[Gdata, List[Gdata]]:
        # This is where you'll implement your collector
        pass
```

In your collector, you'll have access to your section of the config file as a `self.config` variable.  This is actually a `ConfigParser.SectionProxy`, so you can access everything as a dict.

## Configuring Your Plugin
Adding custom configuration settings for your plugin is pretty simple.  Just follow these steps:

1.  Create a section in the config like `[module_name]`.  From the example above, it would be: `[myexample]`
2.  The only setting in this section that is required is `name`.  `name` corresponds to the name of the collector class.  From the example above, that would be `MyCollector`.
3.  Add any custom configuration items in your section that you might want/need.
4.  Finally, in the `[main]` section, enable your plugin by adding your plugin to the `plugins_enabled` list like this:

```
[main]
...
plugins_enabled =
    netstat
    myexample
...
[myexample]
name = MyCollector
...
```

That's about it.  You can obviously enable any of the included plugins.
