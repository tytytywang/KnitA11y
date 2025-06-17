# KnitA11y

## Set Up

<!-- This project may work on older versions of Python, but it was developed with Python 3.9

Particularly if you are a Windows User I highly recommend running this code as a [PyCharm Project](https://www.jetbrains.com/help/pycharm/importing-project-from-existing-source-code.html).

Otherwise: -->

Install the required packages using the `environment.yml` file:

`conda env create -f environment.yml` while in the project directory.

Activate the environment using `conda activate knita11y`

Add the project directory to your `PYTHONPATH`

In Unix machines: `export PYTHONPATH="${PYTHONPATH}:/path/to/your/project/"`

For Windows: `set PYTHONPATH=%PYTHONPATH%;C:\path\to\your\project\`

Now you should be able to access main methods from cmd line (e.g., `python tests\test_simple_knitgraphs.py`)

## Launch the UI
In the command line, type:
```console
cd debugging_tools/knit_ui
```
Next, type:
```console
bokeh serve --show Bokeh_knit_ui.py
```

Some example KnitScripts to begin with:
```console
All rs rounds k 10. All ws rounds k 10.
```
```console
All rs rows k 10. All ws rows k 10.
```

<!-- ### knit_graphs
This package contains the classes used to create a knit graph (`Loop`, `Yarn`, `Knit_Graph`, `Pull_Direction(Enum)`). 

### debugging_tools
This package contains a visualizer method to help visualize simple knit graphs. This may be useful to extend for 
debugging future projects. It also contains a set of simple knitgraph which manually generate some simple textures. 
In future assignments we will make it easier to define more complex knit graphs.

### knitting_machine
This package contains the code to generate knitout code using a model of a v-bed knitting machine. -->
