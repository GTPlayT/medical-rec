let map, userMarker, markers = [];

document.addEventListener("DOMContentLoaded", function () {
    const radiusDropdown = document.getElementById("radiusDropdown");
    const radiusInput = document.getElementById("radius");
    const dropdownItems = document.querySelectorAll(".dropdown-item");

    dropdownItems.forEach((item) => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const value = item.getAttribute("data-value");
            const text = item.textContent.trim();

            // Update the dropdown button text
            radiusDropdown.querySelector(".selected-text").textContent = text;

            // Update the hidden input value
            radiusInput.value = value;

            console.log(`Selected radius: ${value} meters`);
        });
    });
});

function initMap() {
    const defaultLocation = { lat: 28.363880, lng: 75.587010 };

    map = new google.maps.Map(document.getElementById("map"), {
        center: defaultLocation,
        zoom: 15,
    });

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const userLocation = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude,
                };

                map.setCenter(userLocation);

                userMarker = new google.maps.Marker({
                    position: userLocation,
                    map: map,
                    title: "Your Location",
                    icon: {
                        url: "https://maps.google.com/mapfiles/ms/icons/blue-dot.png",
                    },
                });
            },
            (error) => {
                console.warn("Geolocation failed or was denied. Using default location.");
            }
        );
    } else {
        console.warn("Geolocation is not supported by this browser. Using default location.");
    }

    map.addListener("click", (event) => {
        if (userMarker) {
            userMarker.setMap(null);
        }

        userMarker = new google.maps.Marker({
            position: event.latLng,
            map: map,
            title: "Your Location",
            icon: {
                url: "https://maps.google.com/mapfiles/ms/icons/blue-dot.png",
            },
        });
    });
}


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

    const googleMapsLink = `https://www.google.com/maps?q=${doctor.clinic_location.latitude},${doctor.clinic_location.longitude}`;

    const infoWindow = new google.maps.InfoWindow({
        content: `
            <div style="text-align: center;">
                <a href="${googleMapsLink}" target="_blank" title="View Location on Google Maps">
                    <img src="${doctor.profile_image_url}" alt="${doctor.name}" 
                         style="width: 100px; height: 100px; border-radius: 50%; margin-bottom: 10px;">
                </a>
                <br>
                <strong>${doctor.name}</strong><br>
                ₹${doctor.consultation_fee}<br>
                ${formattedSpecializations}<br>
                ${doctor.clinic_address}
            </div>
        `
    });

    marker.addListener("click", () => {
        infoWindow.open(map, marker);
    });
}

function clearMarkers() {
    markers.forEach(marker => marker.setMap(null));
    markers = [];
}


function generateIcons() {
    const icons = [
        "fa-heart", "fa-stethoscope", "fa-temperature-high", "fa-mug-hot"
    ];

    for (let i = 0; i < 50; i++) {
        const iconClass = icons[Math.floor(Math.random() * icons.length)];
        const icon = $('<i>')
            .addClass(`fa ${iconClass} fa-icon`)
            .css({
                top: `${Math.random() * 100}%`,  
                left: `${Math.random() * 100}%`,
                transform: `translate(-50%, -50%)`,
                fontSize: `${Math.random() * 12 + 18}px`,
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

        $(".spinner").show();

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