"""License management CLI commands."""

import click
from colorama import Fore, Style


@click.group()
def license():
    """Manage license and premium features."""
    pass


@license.command()
@click.argument('license_key')
@click.option('--email', prompt=True, help='Your email address')
def activate(license_key: str, email: str):
    """Activate a license key."""
    from src.license_manager import get_license_manager

    click.echo(f"{Fore.CYAN}🔑 Activating license...{Style.RESET_ALL}")

    try:
        manager = get_license_manager()
        license_obj = manager.activate_license(license_key, email)

        click.echo(f"{Fore.GREEN}✓ License activated successfully!{Style.RESET_ALL}\n")
        click.echo(f"{Fore.YELLOW}License Type:{Style.RESET_ALL} {license_obj.license_type.value.upper()}")
        click.echo(f"{Fore.YELLOW}Email:{Style.RESET_ALL} {license_obj.email}")

        if license_obj.expires_at:
            days_left = (license_obj.expires_at - license_obj.issued_at).days
            click.echo(f"{Fore.YELLOW}Valid For:{Style.RESET_ALL} {days_left} days")
        else:
            click.echo(f"{Fore.YELLOW}Valid For:{Style.RESET_ALL} Lifetime")

        click.echo(f"\n{Fore.GREEN}Enabled Features:{Style.RESET_ALL}")
        if license_obj.features:
            for feature in license_obj.features:
                click.echo(f"  ✓ {feature.replace('_', ' ').title()}")
        else:
            click.echo(f"  {Fore.YELLOW}(Free tier - local encryption only){Style.RESET_ALL}")

        click.echo(f"\n{Fore.CYAN}🎉 Thank you for supporting Secure Media Processor!{Style.RESET_ALL}")

    except ValueError as e:
        click.echo(f"{Fore.RED}✗ Activation failed: {e}{Style.RESET_ALL}")
        click.echo(f"\n{Fore.YELLOW}Need help? Visit https://secure-media-processor.com/support{Style.RESET_ALL}")
        raise click.Abort()
    except Exception as e:
        click.echo(f"{Fore.RED}✗ Unexpected error: {e}{Style.RESET_ALL}")
        raise click.Abort()


@license.command()
def status():
    """Show current license status."""
    from src.license_manager import get_license_manager

    click.echo(f"{Fore.CYAN}📋 License Status{Style.RESET_ALL}\n")

    try:
        manager = get_license_manager()
        info = manager.get_license_info()

        if info['active']:
            click.echo(f"{Fore.GREEN}Status:{Style.RESET_ALL} ✓ Active")
            click.echo(f"{Fore.YELLOW}Type:{Style.RESET_ALL} {info['type'].upper()}")
            click.echo(f"{Fore.YELLOW}Email:{Style.RESET_ALL} {info['email']}")

            if info['days_remaining']:
                color = Fore.RED if info['days_remaining'] < 30 else Fore.GREEN
                click.echo(f"{Fore.YELLOW}Expires:{Style.RESET_ALL} {color}{info['days_remaining']} days{Style.RESET_ALL}")
            else:
                click.echo(f"{Fore.YELLOW}Expires:{Style.RESET_ALL} {Fore.GREEN}Never (Lifetime){Style.RESET_ALL}")

            click.echo(f"{Fore.YELLOW}Devices:{Style.RESET_ALL} {info['activated_devices']}/{info['max_devices']}")

            click.echo(f"\n{Fore.GREEN}Enabled Features:{Style.RESET_ALL}")
            if info['features']:
                for feature in info['features']:
                    click.echo(f"  ✓ {feature.replace('_', ' ').title()}")
            else:
                click.echo(f"  {Fore.YELLOW}(None - Free tier){Style.RESET_ALL}")
        else:
            click.echo(f"{Fore.YELLOW}Status:{Style.RESET_ALL} Free Tier")
            click.echo(f"{Fore.YELLOW}Message:{Style.RESET_ALL} {info['message']}")
            click.echo(f"\n{Fore.CYAN}💎 Upgrade to Pro or Enterprise for premium features:{Style.RESET_ALL}")
            click.echo(f"  • Cloud storage (S3, Drive, Dropbox)")
            click.echo(f"  • GPU-accelerated processing")
            click.echo(f"  • Batch operations")
            click.echo(f"  • Multi-cloud sync (Enterprise)")
            click.echo(f"  • Priority support (Enterprise)")
            click.echo(f"\n{Fore.GREEN}Visit https://secure-media-processor.com/pricing{Style.RESET_ALL}")

    except Exception as e:
        click.echo(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")
        raise click.Abort()


@license.command()
@click.confirmation_option(prompt='Are you sure you want to deactivate your license?')
def deactivate():
    """Deactivate license on this device."""
    from src.license_manager import get_license_manager

    click.echo(f"{Fore.CYAN}🔓 Deactivating license...{Style.RESET_ALL}")

    try:
        manager = get_license_manager()
        if manager.deactivate_license():
            click.echo(f"{Fore.GREEN}✓ License deactivated successfully{Style.RESET_ALL}")
            click.echo(f"\n{Fore.YELLOW}You can now activate this license on another device.{Style.RESET_ALL}")
            click.echo(f"{Fore.YELLOW}Free tier features remain available.{Style.RESET_ALL}")
        else:
            click.echo(f"{Fore.YELLOW}No active license found{Style.RESET_ALL}")

    except Exception as e:
        click.echo(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")
        raise click.Abort()
