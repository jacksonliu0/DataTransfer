
__all__ = [
    'main',
]


def main(args=None):
    """主程序入口"""
    import demo
    if args is None:
        import sys
        args = sys.argv[1:]

    hello = demo.Hello()
    return hello.run(*args)
