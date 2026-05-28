// Exclusive script for sidebar.html - Websocket

// WEBSOCKETS
// Identify if we are using http or https
// Use ws to speed up development, without using VMs
let protocol;
if (location.protocol === "https:") {
    protocol = "wss:";
}
else
{
    protocol = "ws:";
}

// GLOBAL VARIABLES
// Create websocket connection without chat_id: this page has no active chat
const ws = new WebSocket(`${protocol}//${location.host}/ws`);

// Upon connecting, register user chats to receive notifications
ws.onopen = function() {
    // Send the user's chat list to subscribe to their notifications
    ws.send(JSON.stringify(
        {
            type: "join",
            chatsNotify: chatsNotify
        }
    ))
}

// Handle messages received from the server
ws.onmessage = function(event) {

    // Deserialize json
    let payload =  JSON.parse(event.data)

    // New message
    if (payload["type"] === "message")
    {

        // Increment unread message counter
        const chat_id_string = String(payload["chat_id"]);
        unreadCounts[chat_id_string] += 1;

        // Updated chat counter
        const count = unreadCounts[chat_id_string];

        // Modify the DOM
        document.querySelectorAll(`span[data-chat-id="${chat_id_string}"]`).forEach(span => {
            span.textContent = count;

            // No new messages
            if (count === 0)
            {
                span.style.display = "none";
            }
            // New messages
            else
            {
                span.style.display = "";
            }
        });

    }
    // Error
    else if (payload["type"] === "error")
    {
        console.error(payload["content"])
    }

}

// Connection closed: invalid token, inactivity, or network error
ws.onclose = function(event) {
    console.log("Connection closed");
}