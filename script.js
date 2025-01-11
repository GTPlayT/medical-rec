let map, userMarker, markers = [];

function initMap() {
    map = new google.maps.Map(document.getElementById("map"), {
        center: { lat: 28.625628, lng: 77.433419 },
        zoom: 12,
    });
    map.addListener("click", (event) => {
        if (userMarker) {
            userMarker.setMap(null);
        }

        // Add a custom marker for the user
        userMarker = new google.maps.Marker({
            position: event.latLng,
            map: map,
            title: "Your Location",
            icon: {
                url: "https://maps.google.com/mapfiles/ms/icons/blue-dot.png", // Custom blue pin
            },
        });
    });
}

// Add doctor markers
function addMarker(doctor) {
    const marker = new google.maps.Marker({
        position: { 
            lat: parseFloat(doctor.clinic_location.latitude), 
            lng: parseFloat(doctor.clinic_location.longitude) 
        },
        map: map,
        title: doctor.name,
    });

    markers.push(marker);

    const formattedSpecializations = doctor.specializations
    ? doctor.specializations
          .replace(/,\s*/g, ', ')
          .replace(/\s*\/\s*/g, ' / ')
    : 'Not specified';

    const infoWindow = new google.maps.InfoWindow({
        content: `<div><strong>${doctor.name}</strong><br>₹${doctor.consultation_fee}<br>${formattedSpecializations}<br>${doctor.clinic_address}</div>`
    });

    marker.addListener("click", () => {
        infoWindow.open(map, marker);
    });
}
// Clear existing markers
function clearMarkers() {
    markers.forEach(marker => marker.setMap(null));
    markers = [];
}
// Generate random icons on the page
// Generate random icons on the page
function generateIcons() {
    const icons = [
        "fa-heart", "fa-stethoscope", "fa-temperature-high", "fa-mug-hot"
    ];

    for (let i = 0; i < 50; i++) {
        const iconClass = icons[Math.floor(Math.random() * icons.length)];
        const icon = $('<i>')
            .addClass(`fa ${iconClass} fa-icon`)
            .css({
                top: `${Math.random() * 100}%`,  // Spread across 100% of the height
                left: `${Math.random() * 100}%`, // Spread across 100% of the width
                transform: `translate(-50%, -50%)`, // Centering each icon
                fontSize: `${Math.random() * 12 + 18}px`, // Random size between 18px and 30px
            });

        $('body').append(icon);
    }
}
$(document).ready(() => {
    initMap();
    generateIcons();

    $("#doctor-search-form").on("submit", function (e) {
        e.preventDefault();
        const symptoms = $("#symptoms").val();
        const radius = $("#radius").val();

        if (!userMarker) {
            alert("Please pin your location on the map!");
            return;
        }

        const location = userMarker.getPosition();
        const data = {
            latitude: location.lat(),
            longitude: location.lng(),
            radius,
            symptoms,
        };

        // Show loading spinner
        $(".spinner").show();

        // Send data to backend
        $.ajax({
            url: "http://127.0.0.1:5000/find-doctors-by-symptoms",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify(data),
            success: (response) => {
                $("#doctor-list").empty();
                clearMarkers();
                $(".spinner").hide();

                if (response.length === 0) {
                    $("#doctor-list").html("<p class='text-center mt-4'>No doctors found in the specified area.</p>");
                    return;
                }

                map.setCenter(location);

                response.forEach((doctor) => {
                    addMarker(doctor);
                    const formattedSummary = doctor.generated_summary
                    ? doctor.generated_summary.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
                    : 'No summary available'
                    const formattedSpecializations = doctor.specializations
                    ? doctor.specializations
                          .replace(/,\s*/g, ', ')
                          .replace(/\s*\/\s*/g, ' / ')
                    : 'Not specified';
                    $("#doctor-list").append(`
                        <div class="col-md-4">
                            <div class="card">
                                <img src="${doctor.profile_image_url}" class="card-img-top" alt="Doctor Image">
                                <div class="card-body">
                                    <h5 class="card-title">${doctor.name}</h5>
                                    <p class="card-text">Specialization: ${formattedSpecializations}</p>
                                    <p class="card-text">Experience: ${doctor.experience}</p>
                                    <p class="card-text">Address: ${doctor.clinic_address}</p>
                                    <p class="card-text">Consultation Fees: ₹${doctor.consultation_fee}</p>
                                    <p class="card-text">Summary: ${formattedSummary}</p>
                                    <a href="${doctor.profile_url}" class="btn btn-custom" target="_blank">View Profile</a>

                                </div>
                            </div>
                        </div>
                    `);
                });
            },
            error: (err) => {
                console.error(err);
                $(".spinner").hide();
                alert("An error occurred while searching for doctors.");
            },
        });
    });
});
console.log()