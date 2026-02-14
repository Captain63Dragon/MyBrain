### This is Javascript. Listener for checkbox changes and updates of the input page with tabs.
### No functionality for filling the tabs in yet, just change of tab visibility and empty content

# set of which ids are selected. These come from the <tr id="<uniqueId>">
# const selectedNodes = new Set();

# export function initializeSelectionTracking() {
#     document.getElementById('search-path-rows').addEventListener('change', (e) => {
#         if (e.target.type === 'checkbox' && e.target.closest('.select-col')) {
#             const nodeId = e.target.closest('tr').id;
            
#             if (e.target.checked) {
#                 selectedNodes.add(nodeId);
#             } else {
#                 selectedNodes.delete(nodeId);
#             }
            
#             updateSelectionUI();
#         }
#     });
# }

# function updateSelectionUI() {
#     const count = selectedNodes.size;
#     const display = document.getElementById('selection-display');
    
#     if (count === 0) {
#         display.textContent = 'Nothing has been selected';
#         // Optionally disable action buttons
#         document.getElementById('delete-selected')?.setAttribute('disabled', 'true');
#     } else {
#         // this would be replaced with updating the content of this tab with sub tabs et al.
#         display.textContent = `${count} item${count > 1 ? 's' : ''} selected`;
#         document.getElementById('delete-selected')?.removeAttribute('disabled');
#     }
# }

# function getSelectedNodeIds() { // this function likely will not be used as the set is available
#     return Array.from(selectedNodes);
# }