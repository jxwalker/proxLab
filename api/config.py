from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Proxmox
    proxmox_host: str = "192.168.8.197"
    proxmox_node: str = "beast"
    proxmox_user: str = "proxlab@pve"
    proxmox_token_name: str = "proxlab"
    proxmox_token_value: str
    proxmox_storage: str = "vmdata"
    proxmox_template_id: int = 9000
    proxmox_vmid_min: int = 200
    proxmox_vmid_max: int = 299
    proxmox_verify_ssl: bool = False

    # TrueNAS
    truenas_host: str = "192.168.8.198"
    truenas_api_key: str
    truenas_pool: str = "bigpool"
    truenas_proxlab_parent: str = "bigpool/proxlab"
    truenas_nfs_server: str = "192.168.8.198"
    truenas_verify_ssl: bool = False

    # Postgres
    postgres_dsn: str  # postgresql://user:pass@host/postgres

    # API auth
    proxlab_api_token: str

    # Protected datasets — never allow deletion of these
    truenas_protected_datasets: list[str] = ["bigpool/vmdata", "bigpool/models"]


settings = Settings()
