// Make form to add cash visible when user wants to add more cash
document.querySelector("#add_more").onclick = function()
{
    document.querySelector("#cash").style.visibility = "visible";
    document.querySelector("#add").style.visibility = "visible";
    document.querySelector("#cancel").style.visibility = "visible";
}

// Make form to add cash hidden if user changes mind
document.querySelector("#cancel").onclick = function()
{
    document.querySelector("#cash").style.visibility = "hidden";
    document.querySelector("#add").style.visibility = "hidden";
    document.querySelector("#cancel").style.visibility = "hidden";
}

// Check to make sure text is entered in the cash amount text field and disable to prevent empty queries
document.querySelector("#cash").onkeyup = function()
{
    if (document.querySelector("#cash").value === "") {
        document.querySelector("#add").disabled = true;
    }
    else
    {
        document.querySelector("#add").disabled = false;
    }
}