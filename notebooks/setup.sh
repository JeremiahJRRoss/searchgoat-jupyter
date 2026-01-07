#!/usr/bin/env bash
#
# searchgoat-jupyter Notebook Environment Setup
# 
# This script sets up a complete Python environment for using searchgoat-jupyter
# with Jupyter notebooks. It works on macOS and modern Linux systems.
#
# Usage: ./setup.sh
#

set -e  # Exit on any error

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="${SCRIPT_DIR}/workspace"
VENV_DIR="${SCRIPT_DIR}/venv"
ENV_FILE="${WORKSPACE_DIR}/.env"
REPO_ROOT="$(dirname "${SCRIPT_DIR}")"

# Colors for output (works on both macOS and Linux)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}→${NC} $1"
}

# =============================================================================
# System Detection
# =============================================================================

detect_system() {
    print_header "Detecting System"
    
    OS="$(uname -s)"
    case "${OS}" in
        Linux*)     
            PLATFORM="Linux"
            ;;
        Darwin*)    
            PLATFORM="macOS"
            ;;
        *)          
            print_error "Unsupported operating system: ${OS}"
            exit 1
            ;;
    esac
    
    print_success "Operating system: ${PLATFORM}"
    
    # Detect Python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        print_error "Python not found. Please install Python 3.10 or later."
        if [[ "${PLATFORM}" == "macOS" ]]; then
            echo "  Run: brew install python@3.12"
        else
            echo "  Run: sudo apt install python3 python3-venv python3-pip"
        fi
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
    PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')
    
    if [[ "${PYTHON_MAJOR}" -lt 3 ]] || [[ "${PYTHON_MAJOR}" -eq 3 && "${PYTHON_MINOR}" -lt 10 ]]; then
        print_error "Python ${PYTHON_VERSION} is too old. Please install Python 3.10 or later."
        exit 1
    fi
    
    print_success "Python version: ${PYTHON_VERSION} (${PYTHON_CMD})"
}

# =============================================================================
# Environment Setup
# =============================================================================

setup_virtual_environment() {
    print_header "Setting Up Python Environment"
    
    # Remove existing venv if present
    if [[ -d "${VENV_DIR}" ]]; then
        print_warning "Removing existing virtual environment..."
        rm -rf "${VENV_DIR}"
    fi
    
    # Create new venv
    print_info "Creating virtual environment..."
    $PYTHON_CMD -m venv "${VENV_DIR}"
    print_success "Virtual environment created at: ${VENV_DIR}"
    
    # Activate venv
    source "${VENV_DIR}/bin/activate"
    print_success "Virtual environment activated"
    
    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --upgrade pip --quiet
    print_success "pip upgraded"
}

install_dependencies() {
    print_header "Installing Dependencies"
    
    # Install searchgoat-jupyter from local source
    print_info "Installing searchgoat-jupyter..."
    pip install -e "${REPO_ROOT}[dev]" --quiet
    print_success "searchgoat-jupyter installed"
    
    # Install Jupyter
    print_info "Installing Jupyter..."
    pip install jupyter --quiet
    print_success "Jupyter installed"
    
    # Verify installation
    print_info "Verifying installation..."
    python -c "from searchgoat_jupyter import SearchClient, __version__; print(f'searchgoat-jupyter v{__version__} ready')"
    print_success "All dependencies installed and verified"
}

# =============================================================================
# Credential Configuration
# =============================================================================

configure_credentials() {
    print_header "Configure Cribl Credentials"
    
    echo "You'll need four pieces of information from Cribl Cloud:"
    echo ""
    echo "  1. Client ID        - From Organization Settings → API Credentials"
    echo "  2. Client Secret    - Generated when you created the API credential"
    echo "  3. Organization ID  - From your URL: https://{workspace}-{org_id}.cribl.cloud"
    echo "  4. Workspace        - From your URL: https://{workspace}-{org_id}.cribl.cloud"
    echo ""
    echo -e "${YELLOW}Tip: Your URL looks like https://main-abc123xyz.cribl.cloud${NC}"
    echo -e "${YELLOW}     In this example: workspace=main, org_id=abc123xyz${NC}"
    echo ""
    
    # Prompt for each credential
    read -p "Enter CRIBL_CLIENT_ID: " CRIBL_CLIENT_ID
    
    # Read secret without echoing (secure input)
    read -s -p "Enter CRIBL_CLIENT_SECRET: " CRIBL_CLIENT_SECRET
    echo ""  # New line after hidden input
    
    read -p "Enter CRIBL_ORG_ID: " CRIBL_ORG_ID
    read -p "Enter CRIBL_WORKSPACE: " CRIBL_WORKSPACE
    
    # Validate inputs aren't empty
    if [[ -z "${CRIBL_CLIENT_ID}" ]] || [[ -z "${CRIBL_CLIENT_SECRET}" ]] || \
       [[ -z "${CRIBL_ORG_ID}" ]] || [[ -z "${CRIBL_WORKSPACE}" ]]; then
        print_error "All credentials are required. Please run the script again."
        exit 1
    fi
    
    # Create workspace directory if needed
    mkdir -p "${WORKSPACE_DIR}"
    
    # Write .env file
    cat > "${ENV_FILE}" << EOF
# Cribl Search API Credentials
# Generated by setup.sh on $(date)
# DO NOT COMMIT THIS FILE TO VERSION CONTROL

CRIBL_CLIENT_ID=${CRIBL_CLIENT_ID}
CRIBL_CLIENT_SECRET=${CRIBL_CLIENT_SECRET}
CRIBL_ORG_ID=${CRIBL_ORG_ID}
CRIBL_WORKSPACE=${CRIBL_WORKSPACE}
EOF
    
    # Secure the file (readable only by owner)
    chmod 600 "${ENV_FILE}"
    
    print_success "Credentials saved to: ${ENV_FILE}"
    print_success "File permissions set to 600 (owner read/write only)"
}

# =============================================================================
# Copy Notebook to Workspace
# =============================================================================

setup_workspace() {
    print_header "Setting Up Workspace"
    
    # Copy test notebook to workspace if not present or older
    NOTEBOOK_SRC="${SCRIPT_DIR}/test_searchgoat.ipynb"
    NOTEBOOK_DST="${WORKSPACE_DIR}/test_searchgoat.ipynb"
    
    if [[ -f "${NOTEBOOK_SRC}" ]]; then
        cp "${NOTEBOOK_SRC}" "${NOTEBOOK_DST}"
        print_success "Test notebook copied to workspace"
    fi
    
    # Create a getting_started notebook
    print_success "Workspace ready: ${WORKSPACE_DIR}"
}

# =============================================================================
# Launch Jupyter
# =============================================================================

launch_jupyter() {
    print_header "Launching Jupyter"
    
    echo ""
    echo "Your environment is ready!"
    echo ""
    echo "  Workspace:    ${WORKSPACE_DIR}"
    echo "  Credentials:  ${ENV_FILE}"
    echo "  Notebook:     test_searchgoat.ipynb"
    echo ""
    echo -e "${GREEN}Starting Jupyter Notebook...${NC}"
    echo -e "${YELLOW}(Press Ctrl+C to stop Jupyter when done)${NC}"
    echo ""
    
    # Change to workspace directory so .env is found
    cd "${WORKSPACE_DIR}"
    
    # Launch Jupyter
    jupyter notebook
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                               ║${NC}"
    echo -e "${GREEN}║   🐐  searchgoat-jupyter Notebook Environment Setup         ║${NC}"
    echo -e "${GREEN}║                                                               ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    
    detect_system
    setup_virtual_environment
    install_dependencies
    configure_credentials
    setup_workspace
    launch_jupyter
}

# Run main
main
