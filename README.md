# Story Grid ComfyUI Tools

Custom ComfyUI nodes and workflows for generating a storyboard grid from a scenario, sending the grid and reference images to a credit/API image node, then slicing the generated sheet into individual cell images.

## Contents

- `custom_nodes/story_grid_tools/`
  - `StoryGridReference`
  - `StoryGridReferenceBatch`
  - `StoryGridModelSwitch`
  - `StoryGridSliceSave`
- `workflows/`
  - `story_grid_credit_3x4.json`
  - `story_grid_credit_3x4_refs_gpt.json`
  - `story_grid_credit_3x4_refs_switch.json`

## Install

Copy `custom_nodes/story_grid_tools` into:

```text
ComfyUI/custom_nodes/story_grid_tools
```

Then restart ComfyUI.

## Workflow Use

Load one of the JSON files from `workflows/` in ComfyUI.

For the switch workflow, use `Story Grid Model Switch`:

- `Gemini Pro`: runs the Gemini branch.
- `GPT Image 2`: runs the OpenAI GPT Image branch.

The switch uses lazy inputs, so only the selected model branch should execute.

Edit the `StoryGridReferenceBatch` reference image paths before running on a different machine.

Generated output is saved by `StoryGridSliceSave` under ComfyUI's `output` directory, including the full generated grid, cropped cells, and a JSON manifest.
