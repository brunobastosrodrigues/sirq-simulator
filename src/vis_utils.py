# src/vis_utils.py
import textwrap

def render_station_visual(model):
    """
    Generates the HTML Digital Twin for the Concept Demo.
    """
    chargers = [a for a in model.schedule.agents if a.status == "Charging"]
    queue = [a for a in model.schedule.agents if a.status == "Queuing"]
    
    # Sort for visual clarity
    if model.strategy == "FIFO":
        queue.sort(key=lambda x: x.unique_id)
    else:
        queue.sort(key=lambda x: x.bid, reverse=True)

    # 1. Render Chargers
    charger_html = ""
    for i in range(model.num_chargers):
        if i < len(chargers):
            truck = chargers[i]
            charger_html += f"""
            <div style="background-color: {truck.color}; color: white; padding: 6px; border-radius: 6px; 
                        width: 80px; text-align: center; border: {truck.border}; margin: 2px; box-shadow: 1px 1px 3px rgba(0,0,0,0.2);">
                <div style="font-size: 14px; font-weight: bold;">⚡ {i+1}</div>
                <div style="font-size: 10px; opacity: 0.9;">${int(truck.bid)}</div>
            </div>"""
        else:
            charger_html += f"""
            <div style="background-color: #f0f2f6; color: #bcccdb; padding: 6px; border-radius: 6px; 
                        width: 80px; text-align: center; border: 2px dashed #dbe4eb; margin: 2px;">
                <div style="font-size: 14px;">💤 {i+1}</div>
            </div>"""

    # 2. Render Queue
    queue_html = ""
    if not queue:
        queue_html = "<div style='color: #aaa; font-style: italic; font-size: 11px; padding: 5px;'>Empty</div>"
    else:
        for truck in queue[:8]: # Limit to 8
            queue_html += f"""
            <div style="background-color: {truck.color}; color: white; padding: 3px 6px; border-radius: 4px; 
                        font-size: 10px; text-align: center; margin: 2px; min-width: 35px; border: {truck.border};" 
                        title="ID: {truck.unique_id}">
                <b>${int(truck.bid)}</b>
            </div>"""
        if len(queue) > 8: 
            queue_html += f"<div style='color: #888; font-size: 9px;'>+{len(queue)-8}</div>"

    return f"""
    <div style="font-family: sans-serif;">
        <div style="display: flex; flex-wrap: wrap; justify-content: center; margin-bottom: 5px;">{charger_html}</div>
        <div style="background-color: #f8f9fa; padding: 5px; border-radius: 6px; border-top: 3px solid #ddd; display: flex; flex-wrap: wrap; justify-content: center;">
            {queue_html}
        </div>
    </div>
    """.replace("\n", "").strip()