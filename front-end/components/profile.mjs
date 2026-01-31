import {apiService} from "../index.mjs";

/**
 * Create a profile component
 * @param {string} template - The ID of the template to clone
 * @param {Object} profileData - The profile data to display
 * @returns {DocumentFragment} - The profile UI
 */
function createProfile(template, {profileData, whoToFollow, isLoggedIn}) {
  if (!template || !profileData) return;
  const profileElement = document
    .getElementById(template)
    .content.cloneNode(true);

  const usernameEl = profileElement.querySelector("[data-username]");
  const bloomCountEl = profileElement.querySelector("[data-bloom-count]");
  const followingCountEl = profileElement.querySelector(
    "[data-following-count]"
  );
  const followerCountEl = profileElement.querySelector("[data-follower-count]");
  const followButtonEl = profileElement.querySelector("[data-action='follow']");
  const unfollowButtonEl = profileElement.querySelector("[data-action='unfollow']");
  const whoToFollowContainer = profileElement.querySelector(".profile__who-to-follow");
  // Populate with data
  usernameEl.querySelector("h2").textContent = profileData.username || "";
  usernameEl.setAttribute("href", `/profile/${profileData.username}`);
  bloomCountEl.textContent = profileData.total_blooms || 0;
  followerCountEl.textContent = profileData.followers?.length || 0;
  followingCountEl.textContent = profileData.follows?.length || 0;
  followButtonEl.setAttribute("data-username", profileData.username || "");
  unfollowButtonEl.setAttribute("data-username", profileData.username || "");
  followButtonEl.hidden = profileData.is_self || profileData.is_following;
  unfollowButtonEl.hidden = profileData.is_self || !profileData.is_following;
  followButtonEl.addEventListener("click", handleFollow);
  unfollowButtonEl.addEventListener("click", handleUnfollow);
  if (!isLoggedIn) {
    followButtonEl.style.display = "none";
    unfollowButtonEl.style.display = "none";
  }

  if (whoToFollow.length > 0) {
    const whoToFollowList = whoToFollowContainer.querySelector("[data-who-to-follow]");
    const whoToFollowTemplate = document.querySelector("#who-to-follow-chip");
    for (const userToFollow of whoToFollow) {
      const wtfElement = whoToFollowTemplate.content.cloneNode(true);
      const usernameLink = wtfElement.querySelector("a[data-username]");
      usernameLink.innerText = userToFollow.username;
      usernameLink.setAttribute("href", `/profile/${userToFollow.username}`);
      const followButton = wtfElement.querySelector("button");
      followButton.setAttribute("data-username", userToFollow.username);
      followButton.addEventListener("click", handleFollow);
     
      if (!isLoggedIn) {
        followButton.style.display = "none";
      }

      whoToFollowList.appendChild(wtfElement);
    }
  } else {
    whoToFollowContainer.innerText = "";
  }

  return profileElement;
}

async function handleFollow(event) {
  const button = event.target;
  const username = button.getAttribute("data-username");
  if (!username) return;

  await apiService.followUser(username);
  await apiService.getWhoToFollow();
}
async function handleUnfollow(event) {
  const button = event.target;
  const username = button.getAttribute("data-username");
  if (!username) return;

  await apiService.unfollowUser(username);
  await apiService.getWhoToFollow();
}


export {createProfile, handleFollow, handleUnfollow};
