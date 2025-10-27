function switchFunction(value) {
  for (const btnid of value) {
    switchbtn = document.getElementById(btnid);
    switchbtn.checked = false;
    }
}


function hidebyid(value) {
  var item = document.getElementById(value);
  item.style.display = "none";
}


function btntogglenhide(btn, btnshowtext, btnhidetext, hideid, clearid) {

  if (btn.innerHTML === btnshowtext) {
        btn.innerHTML = btnhidetext;
      } else {
        btn.innerHTML = btnshowtext;
      }

  if (hideid) {
    var hideblock = document.getElementById(hideid);
    if (hideblock.style.display === "none") {
        hideblock.style.display = "block";
      } else {
        hideblock.style.display = "none";
      }
    }

  if (clearid) {
    var clearblock = document.getElementById(clearid);
    clearblock.innerHTML = "";
    }

}
