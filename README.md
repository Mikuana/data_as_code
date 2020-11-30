# Data as Code

This package provides tools which can be used to strictly define, version control,
and document data. To sum it up, this package treats Data as Code (DaC) in the
instances where that is possible.

This framework is designed for tabular, file-based data sets, and works best with
fixed, unchanging files (although it can also be used for changing data, but some
of the tools in this framework are rendered moot by these changes).

The product generated by this framework is a tabular data set which includes
complete documentation of the original source, intermediate steps of transformation,
and hash sums to guarantee that the data match the associated code.


Stages:
 - Get
 - (Optional) unpack/inflate
 - Parse
 - Transform
 - Package
 - Distribute


# Concepts

 - **Source**: primary data; the "original" that is used by a **recipe**, before
    it has been changed in any way
 
 - **Intermediary**: an intermediate object that is the result of applying
    incremental changes to a *source*, but not the final data product that will
    be produced by the *recipe*. Not meant to be used outside of the recipe, and
    treated as disposable
 
 - **Product**: the ultimate result of the *recipe*, which is intended for use
    outside the *recipe*. Includes the complete *lineage* as a component of the
    packaged product, and optionally includes the *recipe* that was used to
    create it 
 
 - **Recipe**: the set of instructions which use the specified *sources* to
    generate a final data *product*
 
 - **Lineage**: metadata that can be used to trace a *product* back to its
    *source*, which includes all *intermediary* objects
