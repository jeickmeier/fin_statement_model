1. Rename the core/nodes/standard__nodes to node_defn
2. Rename the core/metrics/builtin_organized to metric_defn
3. Ask Claude 4 to review and propose refactors for statements
4. Add detailed README to each of the sub-modules
5. Forecaster is too long of a file, refactor into logical parts
6. Add in the LLM validator / mapping 
7. Add in the more sophisticated excel reader that brings depencency graph from the cell references
8. Add high-level documentation / READMEs that reference the sub-module READMEs
9. Make end to end examples that show capabiltiies of all the functionality
10. Add tear sheet builder
11. Add ways to build up the capital structure - add bond definitions, seniorities, etc --> Calculate interest expense schedules, maturity walls, etc. 
12. 