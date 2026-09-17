import "./style.css";
import {
  listApplications,
  listConfigurations,
  updateConfiguration,
  listFlags,
  updateFlag,
  type Application,
} from "./api";

const applicationsPanel = document.querySelector<HTMLElement>(
  "#applications-panel",
)!;
const applicationsList =
  document.querySelector<HTMLUListElement>("#applications-list")!;
const applicationsStatus = document.querySelector<HTMLElement>(
  "#applications-status",
)!;

const configurationsPanel = document.querySelector<HTMLElement>(
  "#configurations-panel",
)!;
const configurationsHeading = document.querySelector<HTMLElement>(
  "#configurations-heading",
)!;
const configurationsBody = document.querySelector<HTMLTableSectionElement>(
  "#configurations-body",
)!;
const configurationsStatus = document.querySelector<HTMLElement>(
  "#configurations-status",
)!;
const flagsBody =
  document.querySelector<HTMLTableSectionElement>("#flags-body")!;
const flagsStatus = document.querySelector<HTMLElement>("#flags-status")!;
const backButton = document.querySelector<HTMLButtonElement>("#back-button")!;

async function renderApplications(): Promise<void> {
  applicationsStatus.textContent = "Loading applications...";
  applicationsList.innerHTML = "";

  try {
    const applications = await listApplications();
    applicationsStatus.textContent =
      applications.length === 0 ? "No applications yet." : "";

    for (const application of applications) {
      applicationsList.appendChild(renderApplicationItem(application));
    }
  } catch (error) {
    applicationsStatus.textContent = `Failed to load applications: ${(error as Error).message}`;
  }
}

function renderApplicationItem(application: Application): HTMLLIElement {
  const item = document.createElement("li");
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = application.name;
  button.addEventListener("click", () => showConfigurations(application));
  item.appendChild(button);
  return item;
}

async function showConfigurations(application: Application): Promise<void> {
  applicationsPanel.hidden = true;
  configurationsPanel.hidden = false;
  configurationsHeading.textContent = `Configuration - ${application.name}`;
  configurationsStatus.textContent = "Loading configuration entries...";
  configurationsBody.innerHTML = "";
  renderFlags(application);

  try {
    const configurations = await listConfigurations(application.id);
    configurationsStatus.textContent =
      configurations.length === 0 ? "No configuration entries yet." : "";

    for (const configuration of configurations) {
      const row = document.createElement("tr");

      const keyCell = document.createElement("td");
      keyCell.textContent = configuration.configKey;

      const valueCell = document.createElement("td");
      const valueInput = document.createElement("input");
      valueInput.type = "text";
      valueInput.value = configuration.value;
      valueCell.appendChild(valueInput);

      const actionCell = document.createElement("td");
      const saveButton = document.createElement("button");
      saveButton.type = "button";
      saveButton.textContent = "Save";
      saveButton.addEventListener("click", async () => {
        saveButton.disabled = true;
        try {
          await updateConfiguration(
            application.id,
            configuration.configKey,
            valueInput.value,
          );
          configurationsStatus.textContent = `Saved "${configuration.configKey}".`;
        } catch (error) {
          configurationsStatus.textContent = `Failed to save: ${(error as Error).message}`;
        } finally {
          saveButton.disabled = false;
        }
      });
      actionCell.appendChild(saveButton);

      row.append(keyCell, valueCell, actionCell);
      configurationsBody.appendChild(row);
    }
  } catch (error) {
    configurationsStatus.textContent = `Failed to load configuration: ${(error as Error).message}`;
  }
}

async function renderFlags(application: Application): Promise<void> {
  flagsStatus.textContent = "Loading feature flags...";
  flagsBody.innerHTML = "";

  try {
    const flags = await listFlags(application.id);
    flagsStatus.textContent = flags.length === 0 ? "No feature flags yet." : "";

    for (const flag of flags) {
      const row = document.createElement("tr");

      const keyCell = document.createElement("td");
      keyCell.textContent = flag.flagKey;

      const enabledCell = document.createElement("td");
      const enabledCheckbox = document.createElement("input");
      enabledCheckbox.type = "checkbox";
      enabledCheckbox.checked = flag.enabled;
      enabledCell.appendChild(enabledCheckbox);

      const actionCell = document.createElement("td");
      const saveButton = document.createElement("button");
      saveButton.type = "button";
      saveButton.textContent = "Save";
      saveButton.addEventListener("click", async () => {
        saveButton.disabled = true;
        try {
          await updateFlag(
            application.id,
            flag.flagKey,
            enabledCheckbox.checked,
          );
          flagsStatus.textContent = `Saved "${flag.flagKey}".`;
        } catch (error) {
          flagsStatus.textContent = `Failed to save: ${(error as Error).message}`;
        } finally {
          saveButton.disabled = false;
        }
      });
      actionCell.appendChild(saveButton);

      row.append(keyCell, enabledCell, actionCell);
      flagsBody.appendChild(row);
    }
  } catch (error) {
    flagsStatus.textContent = `Failed to load feature flags: ${(error as Error).message}`;
  }
}

backButton.addEventListener("click", () => {
  configurationsPanel.hidden = true;
  applicationsPanel.hidden = false;
});

renderApplications();
