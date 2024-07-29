// image slideshow code:

let slideIndex = 1;
showSlides(slideIndex);

// Next/previous controls
function plusSlides(n) {
  showSlides(slideIndex += n);
}

// Thumbnail image controls
function currentSlide(n) {
  showSlides(slideIndex = n);
}

function showSlides(n) {
  let i;
  let slides = document.getElementsByClassName("mySlides");
  if (n > slides.length) {slideIndex = 1}
  if (n < 1) {slideIndex = slides.length}
  for (i = 0; i < slides.length; i++) {
    slides[i].style.display = "none";
  }
  slides[slideIndex-1].style.display = "block";
}


function makeVisible(id)

{
    let elementID = "pfp-info"
    elementID = elementID.concat(id)
    document.getElementById(elementID).style.visibility = 'visible';
    return false;
}

function makeInvisible(id)

{
    let elementID = "pfp-info"
    elementID = elementID.concat(id)
    document.getElementById(elementID).style.visibility = 'hidden';
    return false;
}



