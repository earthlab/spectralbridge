import numpy as np
from mesma_core import MesmaModels

# load saved files
library = np.load("library_oli.npy")
class_list = np.load("class_list_oli.npy", allow_pickle=True)

print("Library shape:")
print(library.shape)

print("\nFirst 10 class labels:")
print(class_list[:10])

# build MESMA models
models_builder = MesmaModels()

models_builder.setup(class_list)

print("\nMESMA summary:\n")
print(models_builder.summary())
